"use client";

import { ProtectedRoute } from "@/features/auth";
import { LoanAdvanceView } from "@/features/settlements/components/loan-advance-view";

export default function LoanAndAdvancePage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "settlements", action: "read" }}>
      <LoanAdvanceView />
    </ProtectedRoute>
  );
}
