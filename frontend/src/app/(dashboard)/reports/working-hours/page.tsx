"use client";

import { ProtectedRoute } from "@/features/auth";

export default function WorkingHoursReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <div className="p-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mb-2">
          Working Hours Report
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Review total working hours, overtime, and short hours calculations.
        </p>
      </div>
    </ProtectedRoute>
  );
}
