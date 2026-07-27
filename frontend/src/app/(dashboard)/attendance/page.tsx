"use client";

import { ProtectedRoute } from "@/features/auth";
import { AttendanceMasterView } from "@/features/attendance";

export default function AttendancePage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "attendance", action: "read" }}>
      <div className="p-6">
        <AttendanceMasterView />
      </div>
    </ProtectedRoute>
  );
}
