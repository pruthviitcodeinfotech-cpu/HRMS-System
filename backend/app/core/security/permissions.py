"""RBAC permission primitives: the feature catalog, effective-permission model,
and check helpers.

This is the reusable *mechanism* for the project's two-layer authorization model
(feature permission × data scope), plus the canonical **permission catalog**: the
static, code-owned registry of every ``feature_key`` the routers enforce via
``require_permission`` (User-Management/RBAC API Contract §5.4 / §11 Q1). The
permission **data** (rights templates, custom overrides, branch/department access)
is owned by the ``rbac`` module and resolved at request time into an
:class:`EffectivePermissions` snapshot carried on the authenticated principal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.constants.enums import PermissionAction

# ---------------------------------------------------------------------------
# Permission catalog (static, code-owned registry — not a DB table)
# ---------------------------------------------------------------------------

_CRUD = ("create", "read", "edit", "delete")
_CRE = ("create", "read", "edit")
_CR = ("create", "read")
_RE = ("read", "edit")
_R = ("read",)


@dataclass(frozen=True)
class FeatureCatalogEntry:
    """One registered feature: key, display label, grouping, and legal actions."""

    feature_key: str
    feature_label: str
    parent_feature_key: str | None = None
    supported_actions: tuple[str, ...] = _CRUD


def _entry(
    key: str,
    label: str,
    parent: str | None = None,
    actions: tuple[str, ...] = _CRUD,
) -> FeatureCatalogEntry:
    return FeatureCatalogEntry(
        feature_key=key,
        feature_label=label,
        parent_feature_key=parent,
        supported_actions=actions,
    )


#: Every ``feature_key`` enforced by a router's ``require_permission`` guard.
#: ``supported_actions`` reflects the CRUD actions the routers actually check;
#: ``parent_feature_key`` groups sub-features under their owning feature.
PERMISSION_CATALOG: tuple[FeatureCatalogEntry, ...] = (
    # Organization & structure
    _entry("organization", "Organization", None, _CRE),
    _entry("branch", "Branches", "organization", _CRE),
    _entry("department", "Departments", "organization", _CRE),
    _entry("designation", "Designations", "organization", _CRE),
    # Users, roles & access (this module)
    _entry("user_management", "User Management", None, _CRUD),
    _entry("role_management", "Role Management", None, _CRUD),
    _entry("access_management", "Access Management", None, _RE),
    # Employee
    _entry("employee", "Employees", None, _CRUD),
    _entry("employee_salary", "Employee Salary", "employee", _R),
    _entry("employee_document", "Employee Documents", "employee", ("edit",)),
    # Shift & roster (Shift-Management contract §10 matrix:
    # shift / shift_assignment / weekoff / roster)
    _entry("shift", "Shifts", None, _CRUD),
    _entry("shift_assignment", "Shift Assignment", "shift", _CRUD),
    _entry("shift_rotation", "Shift Rotation", "shift", ("create",)),
    _entry("weekoff", "Weekly Off", "shift", _RE),
    _entry("roster", "Roster", "shift", ("read", "edit", "delete")),
    # Attendance
    _entry("attendance", "Attendance", None, _CRE),
    _entry("attendance_punch", "Attendance Punches", "attendance", _CR),
    _entry("attendance_penalty", "Attendance Penalties", "attendance", _CRE),
    # Leave & holidays
    _entry("leave_type", "Leave Types", None, _CRUD),
    _entry("leave_config", "Leave Configuration", None, _RE),
    _entry("leave_balance", "Leave Balances", None, _RE),
    _entry("leave_request", "Leave Requests", None, _CRUD),
    _entry("holiday", "Holidays", None, _CRUD),
    # Approvals
    _entry("approval", "Approvals", None, _RE),
    # Payroll
    _entry("payroll_config", "Payroll Configuration", None, _RE),
    _entry("payroll_group", "Payroll Groups", None, _CRUD),
    _entry("payroll_cycle", "Payroll Cycles", None, _CRE),
    _entry("payroll_processing", "Payroll Processing", None, _RE),
    _entry("payroll_record", "Payroll Records", None, _RE),
    _entry("payroll_adjustment", "Payroll Adjustments", None, _CRUD),
    # Settlements, loans & arrears
    _entry("settlement", "Settlements", None, _RE),
    _entry("loan_advance", "Loans & Advances", None, _CRUD),
    _entry("arrears", "Arrears", None, _RE),
    # Hardware
    _entry("device", "Devices", None, _CRUD),
    # Platform
    _entry("notification", "Notifications", None, _CR),
    _entry("settings", "Settings", None, _RE),
    _entry("dashboard", "Dashboard", None, _R),
    _entry("reports", "Reports", None, _R),
    _entry("audit", "Activity Log", None, _R),
)

_CATALOG_BY_KEY: dict[str, FeatureCatalogEntry] = {
    entry.feature_key: entry for entry in PERMISSION_CATALOG
}


def get_catalog_entry(feature_key: str) -> FeatureCatalogEntry | None:
    """Return the registered catalog entry for ``feature_key`` (``None`` if unknown)."""
    return _CATALOG_BY_KEY.get(feature_key)


def is_known_feature(feature_key: str) -> bool:
    """Return whether ``feature_key`` is registered in the permission catalog."""
    return feature_key in _CATALOG_BY_KEY


def list_catalog(parent_feature_key: str | None = None) -> list[FeatureCatalogEntry]:
    """Return the catalog, optionally filtered to one parent's subtree."""
    if parent_feature_key is None:
        return list(PERMISSION_CATALOG)
    return [
        entry
        for entry in PERMISSION_CATALOG
        if entry.parent_feature_key == parent_feature_key
    ]


# ---------------------------------------------------------------------------
# Effective permissions (resolved per request)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeaturePermission:
    """A single feature's resolved CRUD flags (template ⊕ custom overrides)."""

    feature_key: str
    can_create: bool = False
    can_read: bool = False
    can_edit: bool = False
    can_delete: bool = False

    def allows(self, action: PermissionAction) -> bool:
        return {
            PermissionAction.CREATE: self.can_create,
            PermissionAction.READ: self.can_read,
            PermissionAction.EDIT: self.can_edit,
            PermissionAction.DELETE: self.can_delete,
        }[action]


@dataclass(frozen=True)
class EffectivePermissions:
    """A user's resolved authorization snapshot for a single request.

    ``is_super_admin`` bypasses all feature checks (tenant isolation still applies
    elsewhere). ``branch_ids`` / ``department_ids`` express the data-scope layer.
    """

    is_super_admin: bool = False
    features: dict[str, FeaturePermission] = field(default_factory=dict)
    branch_ids: frozenset[int] = frozenset()
    department_ids: frozenset[int] = frozenset()

    def has_permission(self, feature_key: str, action: PermissionAction) -> bool:
        """Return whether the user may perform ``action`` on ``feature_key``."""
        if self.is_super_admin:
            return True
        feature = self.features.get(feature_key)
        return feature is not None and feature.allows(action)

    def can_access_branch(self, branch_id: int) -> bool:
        return self.is_super_admin or branch_id in self.branch_ids

    def can_access_department(self, department_id: int) -> bool:
        return self.is_super_admin or department_id in self.department_ids


def build_effective_permissions(
    *,
    is_super_admin: bool,
    feature_rows: list[dict[str, object]] | None = None,
    branch_ids: list[int] | None = None,
    department_ids: list[int] | None = None,
) -> EffectivePermissions:
    """Build an :class:`EffectivePermissions` from raw resolved rows.

    ``feature_rows`` are dicts with ``feature_key`` and the four ``can_*`` booleans
    (as produced by the rbac module after merging template + custom overrides).
    """
    features: dict[str, FeaturePermission] = {}
    for row in feature_rows or []:
        key = str(row["feature_key"])
        features[key] = FeaturePermission(
            feature_key=key,
            can_create=bool(row.get("can_create", False)),
            can_read=bool(row.get("can_read", False)),
            can_edit=bool(row.get("can_edit", False)),
            can_delete=bool(row.get("can_delete", False)),
        )
    return EffectivePermissions(
        is_super_admin=is_super_admin,
        features=features,
        branch_ids=frozenset(branch_ids or ()),
        department_ids=frozenset(department_ids or ()),
    )
