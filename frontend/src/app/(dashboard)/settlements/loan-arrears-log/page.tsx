"use client";

import { ProtectedRoute } from "@/features/auth";
import { LoanArrearsLogView } from "@/features/settlements/components/loan-arrears-log-view";

export default function LoanArrearsLogPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "settlements", action: "read" }}>
      <LoanArrearsLogView />
    </ProtectedRoute>
  );
}
