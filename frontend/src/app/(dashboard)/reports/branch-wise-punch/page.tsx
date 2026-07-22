"use client";

import { ProtectedRoute } from "@/features/auth";
import { BranchWisePunchReportView } from "@/features/attendance/components/branch-wise-punch-report-view";

export default function BranchWisePunchReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <BranchWisePunchReportView />
    </ProtectedRoute>
  );
}
