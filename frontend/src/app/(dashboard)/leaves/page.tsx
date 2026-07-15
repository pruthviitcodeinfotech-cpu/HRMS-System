"use client";

import { ProtectedRoute } from "@/features/auth";

export default function LeavesPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "leave_request", action: "read" }}>
      <div>
        <h1 className="text-3xl font-bold mb-2">Leave Requests & Allocations</h1>
        <p className="text-sm text-foreground/75">
          Approve time-off requests, adjust balances, and configure leave policies.
        </p>
      </div>
    </ProtectedRoute>
  );
}
