"use client";

import { ProtectedRoute } from "@/features/auth";
import { DailyPunchReportView } from "@/features/attendance";

export default function DailyPunchReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <DailyPunchReportView />
    </ProtectedRoute>
  );
}
