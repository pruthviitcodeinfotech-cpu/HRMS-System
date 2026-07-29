"use client";

import React, { createContext, useContext } from "react";
import { useAuth } from "../hooks";
import { Permission } from "../types";

interface PermissionContextType {
  permissions: Permission[];
  roles: string[];
  isSuperAdmin: boolean;
  hasPermission: (feature: string, action: "create" | "read" | "edit" | "delete") => boolean;
  hasRole: (role: string | string[]) => boolean;
}

export const PermissionContext = createContext<PermissionContextType | undefined>(undefined);

export const PermissionProvider = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();

  const permissions = user?.permissions || [];
  const roles = user?.roles || [];
  const isSuperAdmin =
    Boolean(user?.isSuperAdmin) ||
    Boolean((user as any)?.is_super_admin) ||
    (roles || []).some(
      (r) =>
        r.toLowerCase() === "super_admin" ||
        r.toLowerCase() === "admin" ||
        r.toLowerCase() === "superadmin" ||
        r.toLowerCase() === "super admin"
    );

  const hasPermission = (
    feature: string,
    action: "create" | "read" | "edit" | "delete"
  ): boolean => {
    if (isSuperAdmin) return true;

    const targetKey = feature.toLowerCase();
    const permission = permissions.find((p) => {
      const fk = (p.feature_key || "").toLowerCase();
      return (
        fk === targetKey ||
        fk === `${targetKey}s` ||
        `${fk}s` === targetKey ||
        fk.startsWith(targetKey) ||
        targetKey.startsWith(fk)
      );
    });

    if (!permission) return true;

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
        return true;
    }
  };

  const hasRole = (role: string | string[]): boolean => {
    if (isSuperAdmin) return true;
    if (Array.isArray(role)) {
      return role.some((r) => roles.includes(r));
    }
    return roles.includes(role);
  };

  return (
    <PermissionContext.Provider
      value={{
        permissions,
        roles,
        isSuperAdmin,
        hasPermission,
        hasRole,
      }}
    >
      {children}
    </PermissionContext.Provider>
  );
};

export const usePermissions = () => {
  const context = useContext(PermissionContext);
  if (context === undefined) {
    throw new Error("usePermissions must be used within a PermissionProvider");
  }
  return context;
};
