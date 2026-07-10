"""Organization / Branch / Department / Designation — module constants.

Feature-permission keys (registered in ``core/security/permissions.py``), the
audit module label, and the explicit sort allowlists used by the list endpoints.
Keeping these here means the router, service, and repository share a single source
of truth for the contract's field names.
"""

from __future__ import annotations

# --- RBAC feature-permission keys (API Contract §2 / §11) --------------------
ORGANIZATION_FEATURE = "organization"
BRANCH_FEATURE = "branch"
DEPARTMENT_FEATURE = "department"
DESIGNATION_FEATURE = "designation"

# --- Audit (Activity Log) module label ---------------------------------------
AUDIT_MODULE = "Organization Management"

# --- Sort allowlists (invalid field -> default) ------------------------------
ORGANIZATION_SORTS = {"org_code", "org_name", "created_at"}
BRANCH_SORTS = {"branch_name", "created_at"}
DEPARTMENT_SORTS = {"dept_name", "created_at"}
DESIGNATION_SORTS = {"designation_name", "created_at"}

# --- Employee status treated as "referencing" for referential guards ---------
ACTIVE_EMPLOYMENT_STATUS = "active"

__all__ = [
    "ORGANIZATION_FEATURE",
    "BRANCH_FEATURE",
    "DEPARTMENT_FEATURE",
    "DESIGNATION_FEATURE",
    "AUDIT_MODULE",
    "ORGANIZATION_SORTS",
    "BRANCH_SORTS",
    "DEPARTMENT_SORTS",
    "DESIGNATION_SORTS",
    "ACTIVE_EMPLOYMENT_STATUS",
]
