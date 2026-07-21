"use client";

import { ProtectedRoute } from "@/features/auth";
import { MusterReportView } from "@/features/attendance/components/muster-report-view";

export default function MusterReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <MusterReportView />
    </ProtectedRoute>
  );
}
