"use client";

import { ProtectedRoute } from "@/features/auth";
import { DesignationList } from "@/features/employees/components/designation-list";

export default function DesignationsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "designation", action: "read" }}>
      <DesignationList />
    </ProtectedRoute>
  );
}
