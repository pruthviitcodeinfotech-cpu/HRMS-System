"use client";

import { ProtectedRoute } from "@/features/auth";
import { AttendanceMasterView } from "@/features/attendance";

export default function AttendanceMasterReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <AttendanceMasterView />
    </ProtectedRoute>
  );
}
