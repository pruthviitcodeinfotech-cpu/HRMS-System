"use client";

import { ProtectedRoute } from "@/features/auth";
import { DepartmentList } from "@/features/employees";

export default function DepartmentsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "department", action: "read" }}>
      <DepartmentList />
    </ProtectedRoute>
  );
}
