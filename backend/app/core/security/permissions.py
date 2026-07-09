"""RBAC permission primitives: the effective-permission model and check helpers.

This is the reusable *mechanism* for the project's two-layer authorization model
(feature permission × data scope). The permission **data** (rights templates,
custom overrides, branch/department access) is owned by the ``rbac`` module and
resolved at request time into an :class:`EffectivePermissions` snapshot carried on
the authenticated principal. No feature catalogue or business rules are hard-coded
here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.constants.enums import PermissionAction


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
