"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../hooks";
import { Skeleton } from "@/components/feedback/skeleton";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: {
    feature: string;
    action: "create" | "read" | "edit" | "delete";
  };
}

export const ProtectedRoute = ({ children, requiredPermission }: ProtectedRouteProps) => {
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    } else if (!isLoading && isAuthenticated && requiredPermission && user) {
      if (!user.isSuperAdmin) {
        const perm = user.permissions.find((p) => p.feature_key === requiredPermission.feature);
        const hasPerm =
          perm &&
          ((requiredPermission.action === "create" && perm.can_create) ||
            (requiredPermission.action === "read" && perm.can_read) ||
            (requiredPermission.action === "edit" && perm.can_edit) ||
            (requiredPermission.action === "delete" && perm.can_delete));

        if (!hasPerm) {
          router.replace("/forbidden");
        }
      }
    }
  }, [isLoading, isAuthenticated, requiredPermission, user, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center p-6">
        <div className="w-full max-w-md space-y-4">
          <Skeleton className="h-8 w-3/4 animate-pulse rounded bg-muted" />
          <Skeleton className="h-32 w-full animate-pulse rounded bg-muted" />
          <Skeleton className="h-10 w-1/2 animate-pulse rounded bg-muted" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requiredPermission && user && !user.isSuperAdmin) {
    const perm = user.permissions.find((p) => p.feature_key === requiredPermission.feature);
    const hasPerm =
      perm &&
      ((requiredPermission.action === "create" && perm.can_create) ||
        (requiredPermission.action === "read" && perm.can_read) ||
        (requiredPermission.action === "edit" && perm.can_edit) ||
        (requiredPermission.action === "delete" && perm.can_delete));

    if (!hasPerm) {
      return null;
    }
  }

  return <>{children}</>;
};
