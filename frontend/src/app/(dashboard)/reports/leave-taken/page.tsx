"use client";

import { ProtectedRoute } from "@/features/auth";
import { LeaveTakenReportView } from "@/features/attendance/components/leave-taken-report-view";

export default function LeaveTakenReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <div className="p-6">
        <LeaveTakenReportView />
      </div>
    </ProtectedRoute>
  );
}
