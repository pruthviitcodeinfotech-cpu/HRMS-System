import { ProtectedRoute } from "@/features/auth";
import { ActivityLogPage } from "@/features/activity-logs";

export const metadata = {
  title: "Activity Logs | Petpooja Payroll",
  description: "View System Activity Logs",
};

export default function ActivityLogs() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "audit", action: "read" }}>
      <ActivityLogPage />
    </ProtectedRoute>
  );
}
