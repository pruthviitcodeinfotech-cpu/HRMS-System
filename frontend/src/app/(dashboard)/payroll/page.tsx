"use client";

import { ProtectedRoute } from "@/features/auth";

export default function PayrollPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div>
        <h1 className="text-3xl font-bold mb-2">Payroll Runs & Calculations</h1>
        <p className="text-sm text-foreground/75">
          Run monthly payroll calculations, view drafts, issue slips, and manage groups.
        </p>
      </div>
    </ProtectedRoute>
  );
}
