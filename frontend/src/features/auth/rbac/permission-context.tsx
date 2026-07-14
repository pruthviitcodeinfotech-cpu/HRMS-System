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
  const isSuperAdmin = !!user?.isSuperAdmin;

  const hasPermission = (
    feature: string,
    action: "create" | "read" | "edit" | "delete"
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
