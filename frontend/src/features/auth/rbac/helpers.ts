import { Permission } from "../types";

/**
 * Checks permission matches directly on array of permission claims.
 */
export const checkPermission = (
  permissions: Permission[],
  feature: string,
  action: "create" | "read" | "edit" | "delete",
  isSuperAdmin = false
): boolean => {
  if (isSuperAdmin) return true;
  const permission = permissions.find((p) => p.feature_key === feature);
  if (!permission) return false;

  switch (action) {
    case "create":
      return permission.can_create;
    case "read":
      return permission.can_read;
    case "edit":
      return permission.can_edit;
    case "delete":
      return permission.can_delete;
    default:
      return false;
  }
};

/**
 * Checks role matches on array of roles.
 */
export const checkRole = (
  userRoles: string[],
  requiredRole: string | string[],
  isSuperAdmin = false
): boolean => {
  if (isSuperAdmin) return true;
  if (Array.isArray(requiredRole)) {
    return requiredRole.some((role) => userRoles.includes(role));
  }
  return userRoles.includes(requiredRole);
};
