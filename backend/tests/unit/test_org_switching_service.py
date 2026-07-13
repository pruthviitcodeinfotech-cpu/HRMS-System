"""Unit tests for Phase 3 Multi-Organization Switching services.

Covers:
    * ``OrganizationMembershipService`` — list_organizations, get_membership,
      is_active_member, get_org_ids
    * ``OrganizationSwitchService``     — switch_organization (success, all
      failure paths), list_user_organizations delegation

All data access is mocked via ``AsyncMock`` so these tests exercise only the
service business rules and orchestration — no database, no Redis, no ASGI.

Fixtures
────────
``membership_service``  — real ``OrganizationMembershipService`` with mocked repos.
``switch_service``      — real ``OrganizationSwitchService`` with mocked repos.
``fake_user``           — existing conftest fixture (simple namespace, active user).
``fake_org``            — org row fixture defined here (active, not deleted).
``fake_membership``     — membership row fixture defined here.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions.base import NotFoundException
from app.modules.auth.exceptions import (
    OrgInactiveException,
    OrgMembershipNotFoundException,
    OrgSwitchNotAllowedException,
)
from app.modules.auth.org_membership_service import OrganizationMembershipService
from app.modules.auth.org_switch_service import OrganizationSwitchService
from app.modules.auth.schemas import AccessTokenResponse, OrganizationSummarySchema


# ===========================================================================
# Shared helpers / fixtures
# ===========================================================================


def _make_org(**overrides: object) -> SimpleNamespace:
    base = {
        "org_id": 10,
        "org_code": "ACME",
        "org_name": "Acme Corp",
        "is_active": True,
        "is_deleted": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_membership(**overrides: object) -> SimpleNamespace:
    base = {
        "id": 1,
        "user_id": 1,
        "org_id": 10,
        "is_primary": True,
        "is_active": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def fake_org() -> SimpleNamespace:
    return _make_org()


@pytest.fixture
def fake_membership() -> SimpleNamespace:
    return _make_membership()


# ---------------------------------------------------------------------------
# OrganizationMembershipService fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def membership_service() -> OrganizationMembershipService:
    """Real service with all repositories replaced by AsyncMock."""
    svc = OrganizationMembershipService(AsyncMock())
    svc._memberships = AsyncMock()
    svc._orgs = AsyncMock()
    return svc


# ---------------------------------------------------------------------------
# OrganizationSwitchService fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def switch_service() -> OrganizationSwitchService:
    """Real service with all sub-dependencies replaced by AsyncMock."""
    svc = OrganizationSwitchService(AsyncMock())
    svc._users = AsyncMock()
    svc._orgs = AsyncMock()
    svc._memberships = AsyncMock()
    svc._audit = AsyncMock()
    return svc


# ===========================================================================
# OrganizationMembershipService tests
# ===========================================================================


class TestOrganizationMembershipService:
    # --- get_user_memberships -----------------------------------------------

    async def test_get_user_memberships_returns_list(
        self, membership_service: OrganizationMembershipService, fake_membership: SimpleNamespace
    ) -> None:
        membership_service._memberships.get_memberships_for_user.return_value = [fake_membership]
        result = await membership_service.get_user_memberships(user_id=1)
        assert result == [fake_membership]
        membership_service._memberships.get_memberships_for_user.assert_awaited_once_with(
            1, active_only=True
        )

    async def test_get_user_memberships_active_only_false(
        self, membership_service: OrganizationMembershipService
    ) -> None:
        membership_service._memberships.get_memberships_for_user.return_value = []
        await membership_service.get_user_memberships(user_id=1, active_only=False)
        membership_service._memberships.get_memberships_for_user.assert_awaited_once_with(
            1, active_only=False
        )

    # --- list_organizations -------------------------------------------------

    async def test_list_organizations_returns_summaries(
        self,
        membership_service: OrganizationMembershipService,
        fake_membership: SimpleNamespace,
        fake_org: SimpleNamespace,
    ) -> None:
        membership_service._memberships.get_memberships_for_user.return_value = [fake_membership]
        membership_service._orgs.get_active_by_id.return_value = fake_org

        result = await membership_service.list_organizations(user_id=1)

        assert len(result) == 1
        assert isinstance(result[0], OrganizationSummarySchema)
        assert result[0].org_id == fake_org.org_id
        assert result[0].org_code == fake_org.org_code
        assert result[0].org_name == fake_org.org_name
        assert result[0].is_primary is True

    async def test_list_organizations_skips_inactive_orgs(
        self,
        membership_service: OrganizationMembershipService,
        fake_membership: SimpleNamespace,
    ) -> None:
        membership_service._memberships.get_memberships_for_user.return_value = [fake_membership]
        # Org no longer active (deleted after membership was created)
        membership_service._orgs.get_active_by_id.return_value = None

        result = await membership_service.list_organizations(user_id=1)
        assert result == []

    async def test_list_organizations_empty_when_no_memberships(
        self, membership_service: OrganizationMembershipService
    ) -> None:
        membership_service._memberships.get_memberships_for_user.return_value = []
        result = await membership_service.list_organizations(user_id=1)
        assert result == []

    async def test_list_organizations_primary_first(
        self,
        membership_service: OrganizationMembershipService,
    ) -> None:
        """Primary org must appear before non-primary orgs in the result."""
        non_primary = _make_membership(org_id=20, is_primary=False)
        primary = _make_membership(org_id=10, is_primary=True)
        membership_service._memberships.get_memberships_for_user.return_value = [
            non_primary,
            primary,
        ]

        def fake_org_lookup(org_id: int) -> SimpleNamespace:  # type: ignore[return]
            return _make_org(org_id=org_id, org_code=f"ORG{org_id}", org_name=f"Org {org_id}")

        membership_service._orgs.get_active_by_id.side_effect = fake_org_lookup

        result = await membership_service.list_organizations(user_id=1)

        assert len(result) == 2
        assert result[0].is_primary is True
        assert result[1].is_primary is False

    # --- get_membership -----------------------------------------------------

    async def test_get_membership_returns_row(
        self,
        membership_service: OrganizationMembershipService,
        fake_membership: SimpleNamespace,
    ) -> None:
        membership_service._memberships.get_membership.return_value = fake_membership
        result = await membership_service.get_membership(user_id=1, org_id=10)
        assert result is fake_membership

    async def test_get_membership_raises_when_not_found(
        self, membership_service: OrganizationMembershipService
    ) -> None:
        membership_service._memberships.get_membership.return_value = None
        with pytest.raises(OrgMembershipNotFoundException) as exc_info:
            await membership_service.get_membership(user_id=1, org_id=99)
        assert exc_info.value.code == "ORG_MEMBERSHIP_NOT_FOUND"

    async def test_get_membership_raises_when_inactive(
        self,
        membership_service: OrganizationMembershipService,
        fake_membership: SimpleNamespace,
    ) -> None:
        fake_membership.is_active = False
        membership_service._memberships.get_membership.return_value = fake_membership
        with pytest.raises(OrgMembershipNotFoundException):
            await membership_service.get_membership(user_id=1, org_id=10)

    # --- is_active_member ---------------------------------------------------

    async def test_is_active_member_true(
        self, membership_service: OrganizationMembershipService
    ) -> None:
        membership_service._memberships.is_active_member.return_value = True
        assert await membership_service.is_active_member(user_id=1, org_id=10) is True

    async def test_is_active_member_false(
        self, membership_service: OrganizationMembershipService
    ) -> None:
        membership_service._memberships.is_active_member.return_value = False
        assert await membership_service.is_active_member(user_id=1, org_id=99) is False

    # --- get_org_ids --------------------------------------------------------

    async def test_get_org_ids_delegates_to_repo(
        self, membership_service: OrganizationMembershipService
    ) -> None:
        membership_service._memberships.get_org_ids_for_user.return_value = [10, 20]
        result = await membership_service.get_org_ids(user_id=1)
        assert result == [10, 20]
        membership_service._memberships.get_org_ids_for_user.assert_awaited_once_with(
            1, active_only=True
        )


# ===========================================================================
# OrganizationSwitchService tests
# ===========================================================================


class TestOrganizationSwitchService:
    # -----------------------------------------------------------------------
    # Helper: build a default-success switch_service fixture state
    # -----------------------------------------------------------------------

    def _setup_happy_path(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
        fake_org: SimpleNamespace,
        fake_membership: SimpleNamespace,
    ) -> None:
        """Configure all mocks for a successful org-switch."""
        switch_service._users.get_active_by_id.return_value = fake_user
        switch_service._memberships.get_membership.return_value = fake_membership
        switch_service._orgs.get_active_by_id.return_value = fake_org
        switch_service._users.get_template_permissions.return_value = []
        switch_service._users.get_custom_permissions.return_value = []
        switch_service._users.get_branch_ids.return_value = []
        switch_service._users.get_department_ids.return_value = []

    # --- Success path -------------------------------------------------------

    async def test_switch_organization_returns_access_token(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
        fake_org: SimpleNamespace,
        fake_membership: SimpleNamespace,
    ) -> None:
        self._setup_happy_path(switch_service, fake_user, fake_org, fake_membership)

        result = await switch_service.switch_organization(
            user_id=1, target_org_id=10, session_id=5
        )

        assert isinstance(result, AccessTokenResponse)
        assert result.access_token  # non-empty JWT
        assert result.token_type == "bearer"
        assert result.expires_in >= 1
        # The refresh token must NOT be included in the response.
        assert result.refresh_token is None

    async def test_switch_organization_audit_written(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
        fake_org: SimpleNamespace,
        fake_membership: SimpleNamespace,
    ) -> None:
        self._setup_happy_path(switch_service, fake_user, fake_org, fake_membership)

        await switch_service.switch_organization(user_id=1, target_org_id=10, session_id=5)

        switch_service._audit.record.assert_awaited_once()
        call_kwargs = switch_service._audit.record.call_args.kwargs
        assert call_kwargs["module"] == "auth"
        assert call_kwargs["sub_module"] == "org_switch"
        assert call_kwargs["org_id"] == 10
        assert call_kwargs["performed_by_user_id"] == 1

    async def test_switch_organization_token_has_target_org(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
        fake_org: SimpleNamespace,
        fake_membership: SimpleNamespace,
    ) -> None:
        """The issued access token must contain the target org_id, not the home org."""
        self._setup_happy_path(switch_service, fake_user, fake_org, fake_membership)
        # User's home org is 1; we are switching to 10.
        fake_user.org_id = 1
        fake_org.org_id = 10
        fake_membership.org_id = 10

        result = await switch_service.switch_organization(
            user_id=1, target_org_id=10, session_id=5
        )

        # Decode just enough to inspect the org_id claim.
        from app.core.security.jwt import verify_token

        claims = verify_token(result.access_token, expected_type="access")
        assert claims["org_id"] == 10

    async def test_switch_organization_permissions_resolved_for_target_org(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
        fake_org: SimpleNamespace,
        fake_membership: SimpleNamespace,
    ) -> None:
        """Branch/department IDs in the token must be from the target org."""
        self._setup_happy_path(switch_service, fake_user, fake_org, fake_membership)
        switch_service._users.get_branch_ids.return_value = [101, 102]
        switch_service._users.get_department_ids.return_value = [201]

        result = await switch_service.switch_organization(
            user_id=1, target_org_id=10, session_id=5
        )

        from app.core.security.jwt import verify_token

        claims = verify_token(result.access_token, expected_type="access")
        assert claims["branch_ids"] == [101, 102]
        assert claims["department_ids"] == [201]
        # Verify the repo was called with the target org, not the home org.
        switch_service._users.get_branch_ids.assert_awaited_once_with(1, 10)
        switch_service._users.get_department_ids.assert_awaited_once_with(1, 10)

    async def test_switch_organization_session_preserved_in_token(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
        fake_org: SimpleNamespace,
        fake_membership: SimpleNamespace,
    ) -> None:
        """The ``sid`` claim in the new token must equal the supplied session_id."""
        self._setup_happy_path(switch_service, fake_user, fake_org, fake_membership)

        result = await switch_service.switch_organization(
            user_id=1, target_org_id=10, session_id=42
        )

        from app.core.security.jwt import verify_token

        claims = verify_token(result.access_token, expected_type="access")
        assert claims["sid"] == "42"

    # --- Failure: user not found -------------------------------------------

    async def test_switch_user_not_found(
        self, switch_service: OrganizationSwitchService
    ) -> None:
        switch_service._users.get_active_by_id.return_value = None
        with pytest.raises(NotFoundException) as exc_info:
            await switch_service.switch_organization(
                user_id=99, target_org_id=10, session_id=5
            )
        assert exc_info.value.code == "USER_NOT_FOUND"

    # --- Failure: user inactive --------------------------------------------

    async def test_switch_inactive_user_rejected(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
    ) -> None:
        fake_user.is_active = False
        switch_service._users.get_active_by_id.return_value = fake_user
        with pytest.raises(OrgSwitchNotAllowedException) as exc_info:
            await switch_service.switch_organization(
                user_id=1, target_org_id=10, session_id=5
            )
        assert exc_info.value.code == "ORG_SWITCH_NOT_ALLOWED"

    # --- Failure: no membership -------------------------------------------

    async def test_switch_no_membership_rejected(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
    ) -> None:
        switch_service._users.get_active_by_id.return_value = fake_user
        switch_service._memberships.get_membership.side_effect = OrgMembershipNotFoundException()
        with pytest.raises(OrgMembershipNotFoundException) as exc_info:
            await switch_service.switch_organization(
                user_id=1, target_org_id=99, session_id=5
            )
        assert exc_info.value.code == "ORG_MEMBERSHIP_NOT_FOUND"

    # --- Failure: org inactive --------------------------------------------

    async def test_switch_inactive_org_rejected(
        self,
        switch_service: OrganizationSwitchService,
        fake_user: SimpleNamespace,
        fake_membership: SimpleNamespace,
    ) -> None:
        switch_service._users.get_active_by_id.return_value = fake_user
        switch_service._memberships.get_membership.return_value = fake_membership
        switch_service._orgs.get_active_by_id.return_value = None  # org inactive/deleted

        with pytest.raises(OrgInactiveException) as exc_info:
            await switch_service.switch_organization(
                user_id=1, target_org_id=10, session_id=5
            )
        assert exc_info.value.code == "ORG_INACTIVE"

    # --- list_user_organizations delegation --------------------------------

    async def test_list_user_organizations_delegates_to_membership_service(
        self,
        switch_service: OrganizationSwitchService,
    ) -> None:
        expected = [
            OrganizationSummarySchema(
                org_id=10, org_code="ACME", org_name="Acme Corp", is_primary=True, is_active=True
            )
        ]
        switch_service._memberships.list_organizations.return_value = expected
        result = await switch_service.list_user_organizations(user_id=1)
        assert result == expected
        switch_service._memberships.list_organizations.assert_awaited_once_with(1)

    # --- _merge_permissions static helper ---------------------------------

    def test_merge_permissions_custom_wins_over_template(self) -> None:
        """Custom overrides must win when a feature appears in both rows."""
        template_row = SimpleNamespace(
            feature_key="payroll.view",
            can_create=False, can_read=True, can_edit=False, can_delete=False,
        )
        custom_row = SimpleNamespace(
            feature_key="payroll.view",
            can_create=False, can_read=True, can_edit=True, can_delete=False,  # override edit
        )
        result = OrganizationSwitchService._merge_permissions([template_row], [custom_row])
        assert result["payroll.view"]["can_edit"] is True

    def test_merge_permissions_template_only(self) -> None:
        row = SimpleNamespace(
            feature_key="employee.view",
            can_create=False, can_read=True, can_edit=False, can_delete=False,
        )
        result = OrganizationSwitchService._merge_permissions([row], [])
        assert "employee.view" in result
        assert result["employee.view"]["can_read"] is True

    def test_merge_permissions_empty_when_no_rows(self) -> None:
        result = OrganizationSwitchService._merge_permissions([], [])
        assert result == {}

    def test_merge_permissions_custom_only(self) -> None:
        """A user with custom permissions but no template should still get those perms."""
        custom_row = SimpleNamespace(
            feature_key="settings.manage",
            can_create=True, can_read=True, can_edit=True, can_delete=True,
        )
        result = OrganizationSwitchService._merge_permissions([], [custom_row])
        assert result["settings.manage"]["can_create"] is True
