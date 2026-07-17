"use client";

import { ProtectedRoute } from "@/features/auth";
import { BranchList } from "@/features/employees";

export default function ManageBranchPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "employee", action: "read" }}>
      <div className="p-6">
        <BranchList />
      </div>
    </ProtectedRoute>
  );
}
