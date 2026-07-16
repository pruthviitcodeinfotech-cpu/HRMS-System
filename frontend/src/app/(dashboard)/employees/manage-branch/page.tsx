"use client";

import { ProtectedRoute } from "@/features/auth";

export default function ManageBranchPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "employee", action: "read" }}>
      <div className="p-6 bg-card border border-border rounded-xl shadow-xs space-y-4">
        <h1 className="text-xl font-bold text-foreground">Manage Branches</h1>
        <p className="text-xs text-muted-foreground">
          Define multiple physical branches, assign office locations, and configure regional settings.
        </p>
      </div>
    </ProtectedRoute>
  );
}
