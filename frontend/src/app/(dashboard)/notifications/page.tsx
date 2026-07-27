"use client";

import { ProtectedRoute } from "@/features/auth";
import { NotificationCenter } from "@/features/notifications/components/notification-center";

export default function NotificationsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "notification", action: "read" }}>
      <NotificationCenter />
    </ProtectedRoute>
  );
}
