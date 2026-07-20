"use client";

import { ProtectedRoute } from "@/features/auth";

export default function LeaveCreatePage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "leave_request", action: "create" }}>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100 mb-2">Leave Create</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Create and configure leave types, allocation policies, and leave balances.
        </p>
      </div>
    </ProtectedRoute>
  );
}
