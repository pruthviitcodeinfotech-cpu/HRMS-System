"use client";

import { ProtectedRoute } from "@/features/auth";

export default function ReportsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <div className="p-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mb-2">
          Reports Overview
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Select a report from the side navigation menu to view detailed analytics and metrics.
        </p>
      </div>
    </ProtectedRoute>
  );
}
