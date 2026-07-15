"use client";

import { ProtectedRoute } from "@/features/auth";

export default function AttendancePage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "attendance", action: "read" }}>
      <div>
        <h1 className="text-3xl font-bold mb-2">Attendance Log & Punches</h1>
        <p className="text-sm text-foreground/75">
          Audit real-time biometric inputs, punch adjustments, and period locking.
        </p>
      </div>
    </ProtectedRoute>
  );
}
