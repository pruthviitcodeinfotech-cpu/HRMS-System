"use client";

import { ProtectedRoute } from "@/features/auth";

export default function ShiftsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "shift", action: "read" }}>
      <div>
        <h1 className="text-3xl font-bold mb-2">Shift Scheduler & Templates</h1>
        <p className="text-sm text-foreground/75">
          Schedule weekly rosters, define shift rules, and manage work schedules.
        </p>
      </div>
    </ProtectedRoute>
  );
}
