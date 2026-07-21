"use client";

import { ProtectedRoute } from "@/features/auth";
import { ShiftWiseReportView } from "@/features/attendance";

export default function ShiftWiseReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <ShiftWiseReportView />
    </ProtectedRoute>
  );
}

