"use client";

import { ProtectedRoute } from "@/features/auth";

export default function HolidayAssignPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "leave_request", action: "edit" }}>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">
          Holiday Assign
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Assign holidays to specific branches, departments, or employee groups.
        </p>
      </div>
    </ProtectedRoute>
  );
}
