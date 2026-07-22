"use client";

import { ProtectedRoute } from "@/features/auth";
import { EmployeeDayWiseMasterView } from "@/features/attendance/components/employee-day-wise-master-view";

export default function EmployeeDayWiseMasterReportPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "reports", action: "read" }}>
      <div className="p-6">
        <EmployeeDayWiseMasterView />
      </div>
    </ProtectedRoute>
  );
}
