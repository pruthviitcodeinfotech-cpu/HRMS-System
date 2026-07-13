"""User Management & RBAC ORM models.

All models are re-exported here so the module can be imported as a single unit
(e.g. by the Alembic migration environment and, later, by repositories).

Phase 2 addition
────────────────
``UserOrganizationMembership`` — the junction table that allows one user identity
to hold memberships in multiple organizations.  All existing models and their
tables are unchanged; this is a purely additive export.
"""

from app.modules.rbac.models.access import UserBranchAccess, UserDepartmentAccess
from app.modules.rbac.models.membership import UserOrganizationMembership
from app.modules.rbac.models.rights import (
    RightsTemplate,
    RightsTemplatePermission,
    UserCustomPermission,
    UserTemplateAssignment,
)
from app.modules.rbac.models.user import User, UserSession

__all__ = [
    "User",
    "UserSession",
    "RightsTemplate",
    "RightsTemplatePermission",
    "UserTemplateAssignment",
    "UserCustomPermission",
    "UserBranchAccess",
    "UserDepartmentAccess",
    # Phase 2 — multi-org membership
    "UserOrganizationMembership",
]

