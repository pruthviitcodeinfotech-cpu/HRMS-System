"use client";

import React from "react";
import { usePermission } from "../hooks";

interface PermissionGuardProps {
  permission: {
    feature: string;
    action: "create" | "read" | "edit" | "delete";
  };
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const PermissionGuard = ({
  permission,
  fallback = null,
  children,
}: PermissionGuardProps) => {
  const hasPermission = usePermission(permission.feature, permission.action);

  if (!hasPermission) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
