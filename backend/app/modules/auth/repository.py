"""Authentication module — data-access layer (async SQLAlchemy).

Pure database operations backing the Authentication API Contract: user lookup for
login, session lifecycle (create / read / revoke / list), and the read queries
needed to build the ``/auth/me`` authorization context. All rows are org-scoped
where the owning table carries ``org_id``.

Phase 2 change (Multi-Organization Switching)
─────────────────────────────────────────────
The four authorization-context methods (``get_template_permissions``,
``get_custom_permissions``, ``get_branch_ids``, ``get_department_ids``) now
accept an explicit ``org_id`` parameter.  This ensures that when a user switches
to a non-primary organization the system resolves only the permissions and data
scope that belong to that organization.  Existing callers pass ``user.org_id``
— behaviour is identical to before.

Design rules:
    * **Reuses the existing RBAC models** (``users`` / ``user_sessions`` and the
      permission/scope tables) — no new models, no schema changes.
    * **Extends** :class:`app.shared.base.repository.BaseRepository`.
    * **No business logic**: password verification, token generation, and the
      template-⊕-custom permission merge live in the service. Repository methods
      only run queries and flush writes; the **service owns the commit boundary**.
    * Timestamps (``now`` / ``when``) are passed in by the caller so queries stay
      deterministic and testable.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.enums import SortOrder
from app.modules.rbac.models import (
    RightsTemplate,
    RightsTemplatePermission,
    User,
    UserBranchAccess,
    UserCustomPermission,
    UserDepartmentAccess,
    UserSession,
    UserTemplateAssignment,
)
from app.modules.employee.models.organization import Branch, Department, Organization
from app.shared.base.repository import BaseRepository


class AuthUserRepository(BaseRepository[User]):
    """Read access to ``users`` plus the RBAC data needed for ``/auth/me``."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    # --- Login / identity ----------------------------------------------------
    async def get_by_email(
        self, org_id: int, email: str, *, include_deleted: bool = False
    ) -> User | None:
        """Return the user with ``email`` in ``org_id`` (soft-deleted excluded by default)."""
        stmt = select(User).where(User.org_id == org_id, User.email == email)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: int) -> User | None:
        """Return a non-deleted user by primary key (``None`` if missing/deleted)."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_login(self, user: User, when: datetime) -> None:
        """Set ``users.last_login_at`` to ``when`` and flush."""
        user.last_login_at = when
        self.session.add(user)
        await self.session.flush()

    # --- Authorization context (for /auth/me and org-switch) ----------------
    async def get_template_permissions(
        self, user_id: int, org_id: int
    ) -> list[RightsTemplatePermission]:
        """Return the permission rows of the user's assigned rights template.

        The join through ``RightsTemplate`` ensures that only templates belonging
        to ``org_id`` are considered.  This is a no-op for users with a single
        org (their template's ``org_id`` always matches), but correctly scopes
        the result when a user switches to a non-primary organization.
        """
        stmt = (
            select(RightsTemplatePermission)
            .join(
                UserTemplateAssignment,
                UserTemplateAssignment.template_id == RightsTemplatePermission.template_id,
            )
            .join(
                RightsTemplate,
                RightsTemplate.id == RightsTemplatePermission.template_id,
            )
            .where(
                UserTemplateAssignment.user_id == user_id,
                RightsTemplate.org_id == org_id,
                RightsTemplate.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_custom_permissions(
        self, user_id: int, org_id: int  # noqa: ARG002  (reserved; custom perms have no org col)
    ) -> list[UserCustomPermission]:
        """Return the user's per-user permission overrides.

        ``org_id`` is accepted for API symmetry with the other permission methods
        and to support future org-scoped custom permissions.  It is not yet used
        in the query because ``user_custom_permissions`` carries no ``org_id``
        column — the field is reserved for Phase 3 schema extension.
        """
        stmt = select(UserCustomPermission).where(UserCustomPermission.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_branch_ids(self, user_id: int, org_id: int) -> list[int]:
        """Return the branch ids the user may access within ``org_id`` (data scope).

        The join through ``branches`` filters to only those branches that belong
        to the active organization.  For single-org users this is equivalent to
        the previous unscoped query; for multi-org users it prevents branches
        from a different org appearing in the active-org token claims.
        """
        stmt = (
            select(UserBranchAccess.branch_id)
            .join(Branch, Branch.branch_id == UserBranchAccess.branch_id)
            .where(
                UserBranchAccess.user_id == user_id,
                Branch.org_id == org_id,
                Branch.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_department_ids(self, user_id: int, org_id: int) -> list[int]:
        """Return the department ids the user may access within ``org_id`` (data scope).

        Same org-scoping rationale as :meth:`get_branch_ids`.
        """
        stmt = (
            select(UserDepartmentAccess.department_id)
            .join(Department, Department.dept_id == UserDepartmentAccess.department_id)
            .where(
                UserDepartmentAccess.user_id == user_id,
                Department.org_id == org_id,
                Department.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class OrgRepository(BaseRepository[Organization]):
    """Lightweight read access to ``organizations`` needed by the org-switch service.

    This repository intentionally exposes only the lookup required for switching:
    verifying that a target org exists and is active.  Full CRUD for organizations
    lives in the Employee Management module.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Organization)

    async def get_active_by_id(self, org_id: int) -> Organization | None:
        """Return the org row if it exists, is active, and is not soft-deleted.

        Returns ``None`` in all other cases so the caller can raise the
        appropriate domain exception (``OrgInactiveException``).
        """
        stmt = select(Organization).where(
            Organization.org_id == org_id,
            Organization.is_active.is_(True),
            Organization.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()


class UserSessionRepository(BaseRepository[UserSession]):
    """Lifecycle operations for ``user_sessions`` (refresh-token sessions)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserSession)

    # --- Create --------------------------------------------------------------
    async def create_session(
        self,
        *,
        user_id: int,
        session_token: str,
        expires_at: datetime | None = None,
        device_info: str | None = None,
        ip_address: str | None = None,
    ) -> UserSession:
        """Insert a new active session row and return it (flushed, not committed)."""
        return await self.create(
            {
                "user_id": user_id,
                "session_token": session_token,
                "expires_at": expires_at,
                "device_info": device_info,
                "ip_address": ip_address,
                "is_active": True,
            }
        )

    # --- Read ----------------------------------------------------------------
    async def get_by_token(self, session_token: str) -> UserSession | None:
        """Return the session with ``session_token`` (unique), or ``None``."""
        stmt = select(UserSession).where(UserSession.session_token == session_token).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_valid_by_token(self, session_token: str, *, now: datetime) -> UserSession | None:
        """Return the session only if it is active, not revoked, and not expired."""
        stmt = (
            select(UserSession)
            .where(
                UserSession.session_token == session_token,
                UserSession.is_active.is_(True),
                UserSession.revoked_at.is_(None),
                or_(UserSession.expires_at.is_(None), UserSession.expires_at > now),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_user(self, session_id: int, user_id: int) -> UserSession | None:
        """Return the session with ``session_id`` iff it belongs to ``user_id``."""
        stmt = (
            select(UserSession)
            .where(UserSession.id == session_id, UserSession.user_id == user_id)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _user_filters(self, user_id: int, *, active_only: bool) -> dict[str, object]:
        filters: dict[str, object] = {"user_id": user_id}
        if active_only:
            filters["is_active"] = True
        return filters

    async def list_for_user(
        self,
        user_id: int,
        *,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 25,
    ) -> list[UserSession]:
        """Return a page of the user's sessions, newest first (reuses ``BaseRepository``)."""
        return await self.list(
            filters=self._user_filters(user_id, active_only=active_only),
            sort_by="created_at",
            sort_order=SortOrder.DESC,
            page=page,
            page_size=page_size,
            allowed_sort={"created_at"},
        )

    async def count_for_user(self, user_id: int, *, active_only: bool = True) -> int:
        """Return the number of the user's sessions (optionally active-only)."""
        return await self.count(filters=self._user_filters(user_id, active_only=active_only))

    # --- Revoke --------------------------------------------------------------
    async def revoke(self, session_row: UserSession, *, when: datetime) -> None:
        """Revoke a single session (``is_active=False``, ``revoked_at=when``) and flush."""
        session_row.is_active = False
        session_row.revoked_at = when
        self.session.add(session_row)
        await self.session.flush()

    async def revoke_all_for_user(
        self,
        user_id: int,
        *,
        when: datetime,
        exclude_session_id: int | None = None,
    ) -> int:
        """Revoke all active sessions for a user (optionally excluding one).

        Returns the number of sessions revoked. Used by logout-everywhere and by
        post-deactivation cleanup.
        """
        conditions = [UserSession.user_id == user_id, UserSession.is_active.is_(True)]
        if exclude_session_id is not None:
            conditions.append(UserSession.id != exclude_session_id)
        stmt = (
            update(UserSession)
            .where(and_(*conditions))
            .values(is_active=False, revoked_at=when)
            .execution_options(synchronize_session=False)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)
