"use client";

import { ProtectedRoute } from "@/features/auth";
import { DepartmentList } from "@/features/employees";

export default function DepartmentsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "employee", action: "read" }}>
      <DepartmentList />
    </ProtectedRoute>
  );
}
