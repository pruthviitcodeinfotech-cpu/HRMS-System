"use client";

import { ProtectedRoute } from "@/features/auth";

export default function EmployeesPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "employee", action: "read" }}>
      <div>
        <h1 className="text-3xl font-bold mb-2">Employee Directory</h1>
        <p className="text-sm text-foreground/75">
          Manage employee records, organizational status, profiles, and histories.
        </p>
      </div>
    </ProtectedRoute>
  );
}
