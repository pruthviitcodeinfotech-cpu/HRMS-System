"use client";

import { ProtectedRoute } from "@/features/auth";
import { WorkingHoursReportView } from "@/features/attendance/components/working-hours-report-view";

export default function WorkingHoursReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <WorkingHoursReportView />
    </ProtectedRoute>
  );
}
